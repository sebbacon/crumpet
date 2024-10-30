# Crumpet

A FastAPI-based document management system with full-text search capabilities and tag management, using SQLite for storage.

## Deployment

Create a Dokku app and configure the domain:

    # Create the app
    dokku apps:create crumpet

    # Set the domain
    dokku domains:add crumpet crumpet.bacon.boutique

Set up persistent storage for the SQLite database:

    # Create storage directory
    dokku storage:ensure-directory crumpet

    # Mount storage for SQLite database
    dokku storage:mount crumpet /var/lib/dokku/data/storage/crumpet:/app/data

Set up SSL certificate:

    # Install the SSL plugin if not already installed
    sudo dokku plugin:install https://github.com/dokku/dokku-letsencrypt.git

    # Configure Let's Encrypt email
    dokku letsencrypt:set crumpet email seb.bacon@gmail.com

    # Enable Let's Encrypt
    dokku letsencrypt:enable crumpet

    # Set up auto-renewal
    dokku letsencrypt:auto-renew crumpet

Set up the required environment variables:

    # Generate a secure API key
    API_KEY=$(openssl rand -hex 32)

    # Set API key
    dokku config:set crumpet API_KEY=$API_KEY

Deploy:

    git remote add dokku dokku@crumpet.bacon.boutique:crumpet
    git push dokku main

## API Documentation

Once deployed, the API documentation is available at:

    https://crumpet.bacon.boutique/docs
    https://crumpet.bacon.boutique/redoc

The API requires an API key to be passed in the `X-API-Key` header for all requests.

## Development

For local development, create a `.env` file with:

    API_KEY=your_dev_key_here
    DATABASE_URL=sqlite:///./dev.db

Then run:

    uvicorn app.main:app --reload

## Loading data

    python -m utils.load_data utils/example_data.json
