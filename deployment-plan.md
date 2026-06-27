# Deployment Plan — FoodieAI Restaurant Concierge

This document outlines the step-by-step guide to deploying the **FoodieAI** application:
- **Backend (FastAPI REST API)**: Hosted on **Railway**
- **Frontend (Vanilla HTML/CSS/JS)**: Hosted on **Vercel**

---

## 1. Deploy the Backend on Railway

Railway is ideal for containerized or Python web applications, reading the `Procfile` automatically.

### Steps:
1. Log in to [Railway](https://railway.app/).
2. Click **New Project** → select **Deploy from GitHub repo**.
3. Choose the `Zomato_AI_Recommendation` repository.
4. Click **Deploy Now**.
5. Once the project container drafts, navigate to the **Variables** tab of the service and add your environment configurations:
   - `GROQ_API_KEY` = `[your_groq_api_key]` *(Retrieve from your Groq Console)*
   - `LLM_MODEL` = `llama-3.3-70b-versatile`
   - `LLM_TEMPERATURE` = `0.7`
   - `LLM_MAX_TOKENS` = `1024`
   - `DATASET_ID` = `ManikaSaini/zomato-restaurant-recommendation`
6. Wait for the deploy to rebuild with variables loaded.
7. Go to the **Settings** tab of the service, scroll down to **Networking**, and click **Generate Domain**.
8. Copy the generated domain (e.g., `https://zomato-ai-production.up.railway.app`). This is your **Production Backend URL**.

---

## 2. Configure the Frontend Domain

Since the frontend is static HTML/JS, it needs to know where to send REST API requests.

### Steps:
1. Open the file [frontend/js/api.js](file:///c:/Users/anshy/OneDrive/Desktop/Zomato%20Milestone/frontend/js/api.js).
2. Locate line 6:
   ```javascript
   const PROD_BACKEND_URL = 'https://your-backend-service.up.railway.app';
   ```
3. Replace the placeholder URL with the copy of your **Railway Production Backend URL** from Step 8. For example:
   ```javascript
   const PROD_BACKEND_URL = 'https://zomato-ai-production.up.railway.app';
   ```
4. Commit and push this change to your GitHub repository:
   ```powershell
   git add frontend/js/api.js
   git commit -m "Update production backend URL in API client"
   git push
   ```

---

## 3. Deploy the Frontend on Vercel

Vercel is designed for ultra-fast static website hosting. We will tell Vercel to host only the `frontend/` directory.

### Steps:
1. Log in to [Vercel](https://vercel.com/).
2. Click **Add New** → **Project**.
3. Import the `Zomato_AI_Recommendation` GitHub repository.
4. In the **Configure Project** settings pane:
   - **Framework Preset**: Select **Other**.
   - **Root Directory**: Click *Edit*, select the `frontend` folder, and click *Continue*. (This makes the `frontend` directory the root of your public web files rather than the entire project folder).
5. Click **Deploy**.
6. Once the build finishes, Vercel will provide you with a production site URL (e.g., `https://zomato-ai-recommendation.vercel.app`).

---

## 4. Production Security & CORS Adjustments (Optional)

Currently, the FastAPI server in [src/main.py](file:///c:/Users/anshy/OneDrive/Desktop/Zomato%20Milestone/src/main.py#L140-L146) allows requests from any website domain via wildcard rules:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    ...
)
```
For production hardening, you can restrict CORS access solely to your Vercel deployment by editing `allow_origins`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://zomato-ai-recommendation.vercel.app"],
    allow_credentials=True,
    ...
)
```
and pushing that to GitHub to let Railway re-deploy.
