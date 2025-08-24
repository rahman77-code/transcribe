# 🔐 RingCentral JWT Authentication Setup Guide

## Step 1: Enable JWT Auth in Your App

You're already on the right page! Here's what to do:

1. **Select "JWT auth flow"** checkbox ✅
2. **Set "Issue refresh tokens?" to "Yes"** ✅
3. **Click "Save" at the bottom of the page**

## Step 2: Generate JWT Credentials

After saving your app with JWT auth enabled:

1. **Look for a new section** that appears:
   - It might say "JWT Credentials", "Credentials", or "Add JWT"
   - This usually appears after you save the JWT auth setting

2. **Click "Add JWT" or "Generate Credentials"**

3. **Download the credentials**:
   - RingCentral will generate a JWT token
   - It might come as a `.json` file or show on screen
   - **IMPORTANT**: Save this token securely - you can't see it again!

## Step 3: Update Your .env File

Add the JWT token to your `.env` file:

```bash
# Remove or comment out the old password credentials
# RINGCENTRAL_USERNAME=(602) 654-1693
# RINGCENTRAL_PASSWORD=Tingringcentral_101

# Add your JWT token
RINGCENTRAL_JWT_TOKEN=your_jwt_token_here

# Keep your Groq API key
GROQ_API_KEY=your_groq_api_key_here
```

## Step 4: Use the JWT Script

Run the new JWT-based script:

```bash
# For August 12, 2025 with 30-second minimum
python ringcentral_jwt_recordings.py

# Or modify the script to change the date/duration
```

## 📋 What JWT Looks Like

Your JWT token will be a long string that looks something like this:
```
eyJraWQiOiI4NzYyZjU5Mi0zNGI4LTQ5ZTMtOGRm...very_long_string...
```

## 🎯 Why JWT is Better

- **No password storage**: More secure
- **Longer validity**: Doesn't expire as quickly
- **Server-to-server**: Perfect for automated scripts
- **No deprecation warnings**: This is RingCentral's recommended approach

## ⚠️ Troubleshooting

If you can't find the JWT generation option after saving:
1. Make sure you clicked "Save" after enabling JWT auth
2. Refresh the page
3. Look for a "Credentials" or "JWT" tab/section
4. Sometimes it's under "Sandbox" or "Production" credentials

Need help? The JWT token is usually found in:
- A "Credentials" section
- A "JWT" tab
- After clicking "Generate New Credentials"
- In the downloaded `.json` file
