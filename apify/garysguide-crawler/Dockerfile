# Use Apify's Puppeteer + Chrome base image
FROM apify/actor-node-puppeteer-chrome:20

# Copy package files
COPY package*.json ./

# Install production dependencies only
RUN npm install --quiet --only=prod --no-optional \
    && echo "Installed NPM packages:" \
    && (npm list || true) \
    && echo "Node.js version:" \
    && node --version \
    && echo "NPM version:" \
    && npm --version

# Copy pre-built dist folder and other necessary files
COPY dist ./dist
COPY .actor ./.actor

# Run the compiled JavaScript
CMD npm start
