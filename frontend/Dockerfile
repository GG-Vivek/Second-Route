# Frontend Dockerfile
FROM node:20-alpine

# Install dependencies for native modules
RUN apk add --no-cache python3 make g++

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1000 -S appgroup \
    && adduser -u 1000 -S appuser -G appgroup \
    && chown -R appuser:appgroup /app
USER appuser

# Expose port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5173 || exit 1

# Run development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]