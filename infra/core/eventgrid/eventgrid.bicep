param communicationServiceName string
param location string
param tags object

// Event Grid System Topic for Azure Communication Services
resource eventGridSystemTopic 'Microsoft.EventGrid/systemTopics@2022-06-15' = {
  name: '${communicationServiceName}-system-topic'
  location: location
  tags: tags
  properties: {
    source: resourceId('Microsoft.Communication/CommunicationServices', communicationServiceName)
    topicType: 'Microsoft.Communication.CommunicationServices'
  }
}

// Event Grid Subscription for Call Events
// Not possible to create this before deploying the application, because of failed validation handshake
// resource eventGridSubscription 'Microsoft.EventGrid/systemTopics/eventSubscriptions@2022-06-15' = {
//   name: 'call-events'
//   parent: eventGridSystemTopic
//   properties: {
//     destination: {
//       endpointType: 'WebHook'
//       properties: {
//         endpointUrl: 'https://callcenterapi-agents.${environmentName}.westeurope.azurecontainerapps.io/acs/incoming'
//       }
//     }
//     filter: {
//       includedEventTypes: [
//         'Microsoft.Communication.CallStarted'
//         'Microsoft.Communication.CallEnded'
//         'Microsoft.Communication.CallTransferAccepted'
//         'Microsoft.Communication.CallTransferFailed'
//       ]
//     }
//   }
// }

output systemTopicName string = eventGridSystemTopic.name 
