# WhatsApp Integration for Car Insurance Claims AI Agent

This guide explains how to integrate your Car Insurance Claims AI Agent with WhatsApp to allow users to send photos of damaged vehicles and receive damage assessments directly in WhatsApp.

## Overview

The integration allows users to:
1. Send text messages to receive instructions
2. Send photos of damaged vehicles
3. Receive detailed damage assessments and cost estimates directly in WhatsApp

## Prerequisites

1. A Meta Developer account
2. A WhatsApp Business API account
3. A deployed instance of the Car Insurance Claims AI Agent API
4. A public URL for your API that WhatsApp can reach

## Setup Instructions

### 1. Create a WhatsApp Business API Account

1. Visit [Meta for Developers](https://developers.facebook.com/)
2. Create a new app or use an existing one
3. Add the WhatsApp product to your app
4. Set up a WhatsApp Business Account

### 2. Configure Your WhatsApp Business API

1. Get your WhatsApp Phone Number ID from the Meta Developer Dashboard
2. Generate a Permanent Access Token for your WhatsApp Business API
3. Create a Webhook Verify Token (any secure random string)

### 3. Configure Your API Environment Variables

Add the following environment variables to your deployment:

```
WHATSAPP_API_URL=https://graph.facebook.com/v17.0
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id_here
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token_here
WHATSAPP_VERIFY_TOKEN=your_webhook_verify_token_here
```

### 4. Configure the Webhooks

1. In the Meta Developer Dashboard, go to your WhatsApp app
2. Set up a webhook with the following:
   - URL: `https://your-api-domain.com/whatsapp/webhook`
   - Verify Token: The same value you set for `WHATSAPP_VERIFY_TOKEN`
   - Subscription Fields: `messages`

### 5. Deploy or Update Your API

Make sure to redeploy your API with the WhatsApp integration code and environment variables.

## Testing the Integration

1. Send a message to your WhatsApp Business Number
2. You should receive a welcome message with instructions
3. Send a photo of a damaged vehicle
4. You should receive a processing message followed by a detailed damage assessment

## Troubleshooting

### Webhook Verification Issues

If webhook verification fails:
- Verify that your API is publicly accessible
- Check that the verify token matches in both your environment variables and the Meta Developer Dashboard
- Ensure the `/whatsapp/webhook` endpoint is correctly exposed

### Message Delivery Issues

If messages aren't being delivered:
- Check your WhatsApp API access token
- Verify your WhatsApp Phone Number ID
- Check the logs on your API server for errors

### Image Processing Issues

If images aren't being processed:
- Check your API logs for errors
- Verify that the Groq API key is valid
- Ensure the image is of sufficient quality and clearly shows the vehicle damage

## Best Practices

1. **User Experience**:
   - Keep response times as quick as possible
   - Provide clear instructions to users
   - Include status updates during processing

2. **Security**:
   - Rotate your access tokens periodically
   - Use HTTPS for your webhook endpoint
   - Validate incoming webhook requests

3. **Error Handling**:
   - Provide helpful error messages to users
   - Implement retry mechanisms for API failures
   - Log all errors for troubleshooting

4. **Performance**:
   - Optimize image processing to minimize response times
   - Consider using background workers for long-running tasks
   - Cache frequent responses if applicable

## WhatsApp API Rate Limits

Be aware of WhatsApp API rate limits:
- 80 messages per second by default
- 1000 template messages per 24 hours to any individual user
- Session messages have a 24-hour window after user contact 