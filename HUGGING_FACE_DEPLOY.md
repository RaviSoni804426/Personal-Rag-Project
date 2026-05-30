# Deploying DataMind to Hugging Face Spaces

> Deploy DataMind on Hugging Face Spaces with Docker runtime for free hosting.

## Quick Deploy (5 minutes)

### Step 1: Create a Hugging Face Account
1. Go to [huggingface.co](https://huggingface.co)
2. Sign up for a free account
3. Verify your email

### Step 2: Create a New Space
1. Click your profile → Spaces
2. Click "Create new Space"
3. Fill in:
   - **Space name**: `datamind`
   - **License**: MIT
   - **SDK**: Docker
   - **Visibility**: Public (or Private)
4. Click "Create Space"

### Step 3: Add Secrets
1. In your Space settings (gear icon → Secrets)
2. Add two secrets:
   - **GROQ_API_KEY**: Your Groq API key from [console.groq.com](https://console.groq.com)
   - **OPENAI_API_KEY**: (Optional) Your OpenAI API key from [platform.openai.com](https://platform.openai.com)

### Step 4: Push Your Repository
```bash
# Clone the Space repository
git clone https://huggingface.co/spaces/your-username/datamind
cd datamind

# Add files from DataMind project
# Copy all files from your DataMind project here

# Push to Hugging Face
git add .
git commit -m "Deploy DataMind to Hugging Face Spaces"
git push
```

### Step 5: Wait for Deployment
- Space will automatically build from the `Dockerfile`
- Watch the build logs in the Space settings
- Once complete, your app is live at: `https://huggingface.co/spaces/your-username/datamind`

## Detailed Setup Instructions

### Prerequisites
- Hugging Face account
- Git installed
- Groq API key (free at [console.groq.com](https://console.groq.com))

### Configuration for Hugging Face

The `Dockerfile` is pre-configured for HF Spaces:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
# Install dependencies, copy files, expose port
CMD ["uvicorn", "datamind.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Environment Variables on Hugging Face

Hugging Face Spaces automatically injects environment variables from your secrets:

```
GROQ_API_KEY → Loaded from secrets
OPENAI_API_KEY → Loaded from secrets  
PORT=8080 → Set automatically
HOST=0.0.0.0 → Set automatically
```

## Troubleshooting

### Build Fails
- Check `requirements.txt` for incompatible packages
- Ensure all dependencies are listed
- Check Docker build logs in Space settings

### App Crashes on Startup
1. Check logs: Space settings → App logs
2. Common issues:
   - `GROQ_API_KEY` not set in secrets
   - Port binding failure (HF uses dynamic ports)
   - Missing dependencies

### 502 Bad Gateway
- Wait 2-3 minutes for the app to start
- Check Space logs for errors
- Restart the Space: settings → "Restart Space"

### Slow Performance
- Hugging Face CPU resources are limited
- First request may take 10-30 seconds
- LLM responses take longer due to API latency

## Getting API Keys

### Groq API Key (Required)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up or log in
3. Navigate to API keys
4. Create new key
5. Copy and paste into HF Spaces secrets

### OpenAI API Key (Optional)
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Go to API keys section
4. Create new key
5. Copy and paste into HF Spaces secrets

## Customization

### Custom Domain
- Upgrade your Space to "Private" for custom domain support
- See HF documentation for domain setup

### Resource Upgrades
- HF Spaces offers CPU/GPU hardware upgrades
- Better for production deployments
- See HF pricing for options

## Monitoring

### Access Logs
- Space settings → App logs
- View real-time application logs

### Usage Stats
- Space settings → Usage
- Monitor CPU/memory usage

## Scaling

### Current Limits
- Single container instance
- ~2GB memory
- CPU-only (unless upgraded)

### For Production Scale
- Deploy to cloud (AWS, GCP, Azure)
- Use container orchestration (Kubernetes)
- Add load balancing
- Use managed vector DB (Pinecone)

## Best Practices

1. **Security**
   - Keep secrets in HF Spaces, not in code
   - Don't expose API keys in public repositories
   - Use environment variables

2. **Performance**
   - Large files (PDFs) may take time to process
   - Batch processing can timeout
   - Consider file size limits

3. **Maintenance**
   - Monitor logs regularly
   - Update dependencies monthly
   - Test locally before deploying

4. **Cost**
   - HF Spaces is free (with compute limitations)
   - API costs depend on usage
   - Groq has free tier and pay-as-you-go

## Support

- **HF Spaces Docs**: https://huggingface.co/docs/hub/spaces
- **DataMind Issues**: https://github.com/yourusername/datamind/issues
- **Community Help**: HF forums and Discord

## Example Space Setup

```bash
# Terminal commands to set up Space
cd /tmp
git clone https://huggingface.co/spaces/username/datamind
cd datamind

# Copy your DataMind project files
cp -r ~/datamind/* .

# Verify files
ls -la

# Push to HF
git add .
git commit -m "Initial DataMind deployment"
git push

# Done! Space will auto-build and deploy
```

---

**Your DataMind instance is now live and publicly accessible!** 🚀

Share the link: `https://huggingface.co/spaces/your-username/datamind`


