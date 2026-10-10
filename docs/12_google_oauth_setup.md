# Google Cloud Console & OAuth 2.0 Setup Guide (Stage 19A)

This document provides the exact, step-by-step procedure required to configure Google OAuth 2.0 in the Google Cloud Console for connecting the official college Gmail account: **`shivaprakashp.cs24@bitsathy.ac.in`**.

---

## 1. Overview & Security Scope

The application requires **READ-ONLY** access to Gmail for academic email summarization and priority triage.

- **Target Account**: `shivaprakashp.cs24@bitsathy.ac.in`
- **Authorized Scope**: `https://www.googleapis.com/auth/gmail.readonly`
- **Security Guarantee**: The application will **never** request permissions to compose, send, delete, or modify emails.
- **Strict Verification**: The backend strictly validates that the authenticated Google account is `shivaprakashp.cs24@bitsathy.ac.in` (case-insensitive). Any other Google account will be immediately rejected and no credentials will be stored.

---

## 2. Google Cloud Console Configuration Procedure

### Step 1: Open Google Cloud Console
1. Navigate to: [https://console.cloud.google.com/](https://console.cloud.google.com/)
2. Log in using your Google account or institutional Google Workspace account.

### Step 2: Create or Select a Project
1. Click the project dropdown at the top of the page.
2. Click **New Project**.
3. Project Name: `Faculty-Email-Summarizer` (or similar).
4. Click **Create** and ensure the project is selected.

### Step 3: Enable the Gmail API
1. In the left navigation menu, go to **APIs & Services** > **Library**.
2. Search for `Gmail API`.
3. Click **Gmail API** and click **Enable**.

### Step 4: Configure the OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**.
2. User Type:
   - If using your college Google Workspace organization domain (`bitsathy.ac.in`), select **Internal** (if available) or **External**.
3. Click **Create**.
4. App Information:
   - **App name**: `AI Email Summarizer Agent`
   - **User support email**: `shivaprakashp.cs24@bitsathy.ac.in`
   - **Developer contact information**: `shivaprakashp.cs24@bitsathy.ac.in`
5. Click **Save and Continue**.
6. **Scopes**:
   - Click **Add or Remove Scopes**.
   - Search for `gmail.readonly` or select `.../auth/gmail.readonly`.
   - Click **Update** and then **Save and Continue**.
7. **Test Users** (If User Type is External):
   - Click **Add Users**.
   - Enter: `shivaprakashp.cs24@bitsathy.ac.in`
   - Click **Add** and **Save and Continue**.

### Step 5: Create OAuth 2.0 Client Credentials
1. Go to **APIs & Services** > **Credentials**.
2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
3. **Application type**: Select **Web application**.
4. **Name**: `Faculty Email Summarizer Local Web Client`
5. **Authorized JavaScript origins**:
   - `http://127.0.0.1:5173`
   - `http://localhost:5173`
6. **Authorized redirect URIs**:
   - `http://127.0.0.1:8001/api/email-provider/gmail/oauth/callback`
7. Click **Create**.
8. A modal will display your **Client ID** and **Client Secret**.

---

## 3. Local Environment Configuration

Copy your Client ID and Client Secret into your local `.env` file (never commit this file to git):

```env
# Google OAuth 2.0 Configuration (Stage 19A)
GOOGLE_CLIENT_ID=your_client_id_from_google_console.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_from_google_console
GOOGLE_REDIRECT_URI=http://127.0.0.1:8001/api/email-provider/gmail/oauth/callback
COLLEGE_GMAIL_ACCOUNT=shivaprakashp.cs24@bitsathy.ac.in
GMAIL_TOKEN_PATH=./backend/app/database/gmail_token.json
```

---

## 4. Connecting and Verifying the Account

1. Start the application servers:
   ```bash
   # Backend:
   python -m uvicorn backend.main:app --host 127.0.0.1 --port 8001 --reload

   # Frontend:
   npm run dev -- --host 127.0.0.1 --port 5173
   ```
2. Navigate to: `http://127.0.0.1:5173/settings`.
3. Locate the **College Gmail Connection (Stage 19A)** card.
4. Click **Connect College Gmail**.
5. You will be redirected to Google's official account selection page:
   - Select **`shivaprakashp.cs24@bitsathy.ac.in`**.
   - Review the requested permission (`View your email messages and settings`).
   - Click **Allow / Continue**.
6. Google redirects to the FastAPI callback (`/api/email-provider/gmail/oauth/callback`).
7. The backend verifies that the authenticated email matches `shivaprakashp.cs24@bitsathy.ac.in`.
8. The credentials are encrypted/stored locally at `backend/app/database/gmail_token.json`.
9. The UI displays:
   - Status: **Connected**
   - Authenticated Account: **`shivaprakashp.cs24@bitsathy.ac.in`**
   - Permission Scope: **Read-Only (`gmail.readonly`)**

---

## 5. Disconnection and Revocation

To revoke and delete local credentials:
1. In `http://127.0.0.1:5173/settings`, click **Disconnect**.
2. The backend deletes `gmail_token.json` and resets provider memory.
3. Alternatively, send an authenticated POST request:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/email-provider/gmail/disconnect
   ```
