# Telegram Integration for Car Insurance Claims AI Agent

This guide explains how to integrate your Car Insurance Claims AI Agent with Telegram to allow users to send photos of damaged vehicles and receive damage assessments directly in Telegram.

## Overview

The integration allows users to:
1. Send text messages to receive instructions
2. Send photos of damaged vehicles
3. Receive detailed damage assessments and cost estimates directly in Telegram

## Prerequisites

1. A Telegram account
2. A Telegram bot token (obtained from BotFather)
3. A deployed instance of the Car Insurance Claims AI Agent API
4. A public URL for your API that Telegram can reach

## Advantages of Telegram

- **Completely free**: No messaging limits or fees
- **Simpler API**: No complex authentication or approval processes
- **No session limits**: Users can message anytime
- **Better multimedia handling**: Easy to send and receive photos
- **No business account required**: Works with any Telegram bot
- **Webhook setup is straightforward**: No verification challenges

## Setup Instructions

### 1. Create a Telegram Bot

1. Open Telegram and search for "@BotFather"
2. Start a chat with BotFather and type `/newbot`
3. Follow the prompts to name your bot (e.g., "Car Damage Assessor")
4. Choose a username ending with "bot" (e.g., "CarDamageAssessorBot")
5. **Save the API token** BotFather gives you - you'll need it for configuration

### 2. Configure Your API Environment Variables

Add the following environment variable to your deployment:

```
TELEGRAM_BOT_TOKEN_CAR_ASSESSOR=your_telegram_bot_token_here
```

### 3. Deploy or Update Your API

Make sure to deploy your API with the Telegram integration code and environment variables using the provided script:

```bash
# Set your Telegram bot token as an environment variable
export TELEGRAM_BOT_TOKEN_CAR_ASSESSOR=your_telegram_bot_token_here

# Run the deployment script
./deploy-telegram-bot.sh
```

### 4. Configure the Telegram Webhook

After deploying your API, you need to configure the webhook for your Telegram bot:

1. Visit the webhook setup URL provided in the deployment output:
   ```
   https://your-api-domain.com/telegram/set-webhook
   ```

2. This will automatically configure your bot to send messages to your API

## Testing the Integration

1. Open Telegram and search for your bot by its username (e.g., `@CarDamageAssessorBot`)
2. Start a chat with your bot
3. Send a message or type `/start` to receive instructions
4. Send a photo of a damaged vehicle
5. The bot will process the image and respond with a detailed damage assessment

## Troubleshooting

### Webhook Issues

If the webhook isn't working:
- Verify that your API is publicly accessible
- Check that the bot token is correct
- Ensure the `/telegram/webhook` endpoint is correctly exposed
- Visit `/telegram/webhook-info` to check the current webhook status

### Message Delivery Issues

If messages aren't being delivered:
- Check your bot token
- Verify that your webhook is correctly set up
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
   - Keep your bot token secure
   - Use HTTPS for your webhook endpoint
   - Validate incoming webhook requests

3. **Error Handling**:
   - Provide helpful error messages to users
   - Implement retry mechanisms for API failures
   - Log all errors for troubleshooting

4. **Performance**:
   - Optimize image processing to minimize response times
   - Use background tasks for long-running operations
   - Handle multiple concurrent requests efficiently 