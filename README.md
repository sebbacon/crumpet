# Crumpet

A FastAPI-based document management system with full-text search capabilities and tag management, using SQLite for storage.

## Deployment

Create a Dokku app:

    dokku apps:create crumpet

Set up persistent storage for the SQLite database:

    # Create storage directory
    dokku storage:ensure-directory crumpet
    
    # Mount storage for SQLite database
    dokku storage:mount crumpet /var/lib/dokku/data/storage/crumpet:/app/data

Set up the required environment variables:

    # Generate a secure API key
    API_KEY=$(openssl rand -hex 32)
    
    # Set API key
    dokku config:set crumpet API_KEY=$API_KEY

Deploy:

    git remote add dokku dokku@your-server:crumpet
    git push dokku main

## API Documentation

Once deployed, the API documentation is available at:

    https://crumpet.your-server/docs
    https://crumpet.your-server/redoc

The API requires an API key to be passed in the `X-API-Key` header for all requests.

## Development

For local development, create a `.env` file with:

    API_KEY=your_dev_key_here
    DATABASE_URL=sqlite:///./dev.db

Then run:

    uvicorn app.main:app --reload
