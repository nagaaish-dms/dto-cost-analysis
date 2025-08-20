#!/bin/bash
set -e

echo "Setting up DTO Cost Analysis Agent..."

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Set AWS region if not already set
export AWS_REGION=${AWS_REGION:-us-east-1}

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure environment: cp .env.example .env && edit .env"
echo "2. Test setup: python test_setup.py"
echo "3. Run analysis: python run_dto_analysis.py"
echo ""
echo "For detailed instructions, see DEPLOYMENT_GUIDE.md"
