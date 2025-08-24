# 🔑 How to Generate a New JWT Token

Your current JWT token was created BEFORE you added the Call Recording permissions.
You need a NEW JWT token that includes these permissions.

## Steps to Generate New JWT Token:

1. **Go to RingCentral Developer Console**
   - https://developers.ringcentral.com/

2. **Navigate to Your App**
   - Click on "transcribe call recording"

3. **Go to Credentials Tab**
   - Look for "Credentials" at the top of the page
   - Click on it

4. **Find JWT Credentials Section**
   - You'll see your existing JWT credential
   - There should be a "Delete" or "Revoke" option - click it
   - Confirm deletion of the old JWT

5. **Create New JWT**
   - Click "Create JWT" or "Add Personal JWT"
   - Give it a name (e.g., "Recording Access JWT")
   - Click "Create" or "Generate"

6. **Copy the New JWT Token**
   - It will look like: `eyJraWQiOiI4NzYyZjU5OGQwNTk0NGRiODZiZjVjYTk3ODA0NzYwOCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0...`
   - Copy the ENTIRE token

7. **Update Your .env File**
   - Replace the old JWT token with the new one:
   ```
   RINGCENTRAL_JWT_TOKEN=paste_your_new_jwt_token_here
   ```

## Important Notes:

- ✅ The new JWT will include all your current permissions
- ✅ This includes the newly added Call Recording permissions
- ⏱️ The new token should work immediately
- 🔒 Keep the token secure - don't share it publicly

## After Updating the Token:

Run the script again:
```bash
python fetch_recordings_final.py 2025-08-12 30
```

This should now successfully fetch your recordings!
