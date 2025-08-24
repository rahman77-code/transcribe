#!/bin/bash
# Setup script for Oracle Cloud Always Free tier
# Run this once on your Oracle Cloud VM to set up automatic daily processing

echo "🚀 Setting up Oracle Cloud for daily call transcription..."

# Update system
sudo apt update
sudo apt upgrade -y

# Install Python and Git
sudo apt install python3-pip git cron -y

# Clone your repository (replace with your actual repo URL)
echo "📥 Cloning repository..."
# git clone YOUR_REPO_URL_HERE
# cd YOUR_REPO_DIRECTORY

# Install Python dependencies
echo "📦 Installing Python packages..."
pip3 install -r requirements.txt

# Create environment file template
echo "📝 Creating environment file..."
cat > .env << 'EOF'
# Replace these with your actual credentials
RC_CLIENT_ID=your_ringcentral_client_id
RC_CLIENT_SECRET=your_ringcentral_client_secret
RC_JWT=your_ringcentral_jwt_token
GROQ_API_KEY_1=your_groq_api_key_1
GROQ_API_KEY_2=your_groq_api_key_2
GROQ_API_KEY_3=your_groq_api_key_3
# Add more Groq keys as needed
EOF

echo "⚠️  IMPORTANT: Edit the .env file with your real API keys:"
echo "   nano .env"
echo ""

# Create log rotation
sudo tee /etc/logrotate.d/call-transcription << EOF
$HOME/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
EOF

# Create cron job for daily execution
echo "⏰ Setting up daily cron job..."
SCRIPT_DIR=$(pwd)
CRON_JOB="0 2 * * * cd $SCRIPT_DIR && /usr/bin/python3 daily_call_processor_dev_optimized.py >> transcription_cron.log 2>&1"

# Add to crontab
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your real API keys: nano .env"
echo "2. Test the script manually: python3 daily_call_processor_dev_optimized.py"
echo "3. Check cron job was added: crontab -l"
echo "4. Monitor logs: tail -f transcription_cron.log"
echo ""
echo "🕐 The script will now run automatically every day at 2 AM server time"
echo "📁 Results will be saved in: daily_recordings/"
