#!/bin/sh


# Set SUPABASE_URL dynamically
# Necessary to point to the correct supabase url locally
# In CI, the supabase url is set in the .env file
if [ "$ENVIRONMENT" != "local" ]; then
  export SUPABASE_URL="${SUPABASE_URL}"
else
  export SUPABASE_URL="http://host.docker.internal:54321"
fi

# Debug output
echo "Using SUPABASE_URL: $SUPABASE_URL"

# Execute the main process
exec "$@" 