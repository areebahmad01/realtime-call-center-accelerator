from aiohttp import web
import os
import asyncio
import httpx

from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    TextSource,
    RecognizeInputType
)

class AcsCaller:
    def __init__(self, source_number: str, acs_connection_string: str, acs_callback_path: str, _unused_ws_path: str):

        self.source_number = source_number
        self.acs_connection_string = acs_connection_string
        self.acs_callback_path = acs_callback_path

        # NEW CONFIGS
        self.foundry_webhook_url = os.environ.get("FOUNDRY_WEBHOOK_URL")
        self.cognitive_services_endpoint = os.environ.get("COGNITIVE_SERVICES_ENDPOINT")
        self.cognitive_services_endpoint_key = os.environ.get("COGNITIVE_SERVICES_ENDPOINT_KEY")
        

        if not self.foundry_webhook_url:
            raise ValueError("FOUNDRY_WEBHOOK_URL not set")

        if not self.cognitive_services_endpoint:
            raise ValueError("COGNITIVE_SERVICES_ENDPOINT not set")

    # ==========================================
    # OUTBOUND CALL
    # ==========================================
    async def initiate_call(self, target_number: str):
        client = CallAutomationClient.from_connection_string(self.acs_connection_string)

        target = PhoneNumberIdentifier(target_number)
        source = PhoneNumberIdentifier(self.source_number)

        print(f"Calling {target_number}...")

        client.create_call(
            target_participant=target,
            callback_url=self.acs_callback_path,
            source_caller_id_number=source,
            cognitive_services_endpoint=f"{self.cognitive_services_endpoint};{self.cognitive_services_endpoint_key}" # ✅ IMPORTANT
        )

    # ==========================================
    # FOUNDRY CALL
    # ==========================================
    async def ask_foundry_agent(self, user_text: str, call_connection_id: str) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "languageCode": "en",
                "fulfillmentInfo": {"tag": "call-foundry"},
                "sessionInfo": {
                    "session": f"sessions/{call_connection_id}",
                    "parameters": {}
                },
                "text": user_text
            }

            try:
                response = await client.post(self.foundry_webhook_url, json=payload)
                response.raise_for_status()
                data = response.json()

                return data["fulfillment_response"]["messages"][0]["text"]["text"][0]

            except Exception as e:
                print("Foundry error:", str(e))
                return "Sorry, I am having trouble right now."

    async def process_and_respond(self, call_client, user_text, target_participant):
        reply = await self.ask_foundry_agent(user_text, call_client._call_connection_id)

        print("Agent reply:", reply)

        tts = TextSource(
            text=reply,
            source_locale="en-US",
            voice_name="en-US-JennyNeural"
        )

        try:
            call_client.start_recognizing_media(
                input_type=RecognizeInputType.SPEECH,
                target_participant=target_participant,
                play_prompt=tts,
                interrupt_prompt=True,
                initial_silence_timeout=15,
                end_silence_timeout=2,
                speech_language="en-US"
            )
        except Exception as e:
            print("Speech error:", e)

    # ==========================================
    # INBOUND + OUTBOUND EVENT HANDLER (UNIFIED)
    # ==========================================
    async def inbound_call_handler(self, request):
        # 🔹 Event Grid validation
        if request.headers.get('aeg-event-type') == 'SubscriptionValidation':
            data = await request.json()
            return web.json_response({
                'validationResponse': data[0]['data']['validationCode']
            })

        events = await request.json()

        for event in events:
            event_type = event.get("eventType") or event.get("type")
            data = event.get("data", {})

            call_id = data.get("callConnectionId")

            print(f"Event: {event_type}, Call ID: {call_id}")

            # ==========================================
            # INCOMING CALL
            # ==========================================
            if event_type == "Microsoft.Communication.IncomingCall":
                incoming_call_context = data["incomingCallContext"]

                CallAutomationClient.from_connection_string(
                    self.acs_connection_string
                ).answer_call(
                    incoming_call_context,
                    self.acs_callback_path,
                    cognitive_services_endpoint=f"{self.cognitive_services_endpoint};{self.cognitive_services_endpoint_key}"
                )

                print("Incoming call answered")

            # ==========================================
            # CALL CONNECTED (BOTH INBOUND + OUTBOUND)
            # ==========================================
            elif event_type == "Microsoft.Communication.CallConnected":
                call_client = CallAutomationClient.from_connection_string(
                    self.acs_connection_string
                ).get_call_connection(call_id)

                target = PhoneNumberIdentifier(self.source_number)

                greeting = TextSource(
                    text="Hello! I am your AI assistant. How can I help you today?",
                    source_locale="en-US",
                    voice_name="en-US-JennyNeural"
                )

                call_client.start_recognizing_media(
                    input_type=RecognizeInputType.SPEECH,
                    target_participant=target,
                    play_prompt=greeting,
                    interrupt_prompt=True,
                    initial_silence_timeout=10,
                    end_silence_timeout=2
                )

                print("Greeting sent, listening...")

            # ==========================================
            # USER SPOKE
            # ==========================================
            elif event_type == "Microsoft.Communication.RecognizeCompleted":
                if data.get("recognitionType") == "speech":
                    user_text = data.get("speechResult", {}).get("speech")

                    print("User said:", user_text)

                    call_client = CallAutomationClient.from_connection_string(
                        self.acs_connection_string
                    ).get_call_connection(call_id)

                    target = PhoneNumberIdentifier(self.source_number)

                    asyncio.create_task(
                        self.process_and_respond(call_client, user_text, target)
                    )

            # ==========================================
            # FAIL SAFE
            # ==========================================
            elif event_type == "Microsoft.Communication.RecognizeFailed":
                print("Recognition failed, retrying...")

        return web.Response(status=200)
