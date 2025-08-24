# 🔐 Adding Your 11 API Keys to GitHub Secrets

## 📋 Quick Copy List for GitHub Secrets

Add these one by one to your GitHub repository (Settings → Secrets → Actions → New repository secret):

### RingCentral Secrets
| Name | Value |
|------|-------|
| `RC_CLIENT_ID` | `VNKRmCCWukXcPadmaLZoMu` |
| `RC_CLIENT_SECRET` | `37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ` |
| `RC_JWT` | `eyJraWQiOiI4NzYyZjU5OGQwNTk0NGRiODZiZjVjYTk3ODA0NzYwOCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJhdWQiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbS9yZXN0YXBpL29hdXRoL3Rva2VuIiwic3ViIjoiNjMzMjQ0MDQwMDgiLCJpc3MiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbSIsImV4cCI6Mzg5NTE2Nzk4NCwiaWF0IjoxNzQ3Njg0MzM3LCJqdGkiOiJCbG1KZ1JVblNCU0Fld2NMNDhvdEZRIn0.Cx2UAGelOzaQkwcqt3c1Ijo_-5gDjO_i7cJfPEc6fJGRUxMwkhYwQGOG7-A9_wh2woaiEdVHMsoNyMgh9_0pk94_Hov8hjroMlN0d685bOYMciEsynWLvFZG74JHlyLj8a4uTmlk_EwVX3Eos8_mQNr4uc8sZhGzhLkGyBqwjBQsWdRY0niemFWvtep8qPvjp2KkEwEonH7vOFdodUB__7D-6YR6tn5OV_kjV2EzH8yBSGzF8y75acf9HcfRIMoTe7z2fF8XtYqdX0sn9c-b16yFc05atYrW5CEuctctGZMzR4AvizSZbDSg0OZn9IpL3Um0S8ALc00DTCaB9NfA6A` |

### Groq API Keys
| Name | Value |
|------|-------|
| `GROQ_API_KEY_1` | `your_groq_api_key_1_here` |
| `GROQ_API_KEY_2` | `your_groq_api_key_2_here` |
| `GROQ_API_KEY_3` | `your_groq_api_key_3_here` |
| `GROQ_API_KEY_4` | `your_groq_api_key_4_here` |
| `GROQ_API_KEY_5` | `your_groq_api_key_5_here` |
| `GROQ_API_KEY_6` | `your_groq_api_key_6_here` |
| `GROQ_API_KEY_7` | `your_groq_api_key_7_here` |
| `GROQ_API_KEY_8` | `your_groq_api_key_8_here` |
| `GROQ_API_KEY_9` | `your_groq_api_key_9_here` |
| `GROQ_API_KEY_10` | `your_groq_api_key_10_here` |
| `GROQ_API_KEY_11` | `your_groq_api_key_11_here` |

### HubSpot (Optional)
| Name | Value |
|------|-------|
| `HUBSPOT_ACCESS_TOKEN` | `your_hubspot_access_token_here` |

## 🚀 Step by Step

1. Go to your GitHub repository
2. Click **Settings** (in the repo menu)
3. Click **Secrets and variables** → **Actions**
4. For each secret above:
   - Click **New repository secret**
   - Enter the **Name** exactly as shown
   - Paste the **Value**
   - Click **Add secret**

## ✅ Verify Everything is Set

After adding all secrets, you should see 15 secrets total:
- 3 RingCentral secrets
- 11 Groq API keys  
- 1 HubSpot token

## 🎯 Ready to Deploy!

Once all secrets are added, your GitHub Actions workflow will automatically use all 11 API keys for maximum processing power!
