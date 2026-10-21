# The storefront Dockerfile (Phase 10).
#
# The shop window is a separate application on its own port. It shares
# the design system with the operator's application, so the build context
# is the repository root rather than this directory: the primitives live
# in ``frontend/src``.
FROM node:20-alpine

RUN apk add --no-cache python3 make g++

WORKDIR /app

# The design system is imported rather than copied, so the storefront
# cannot drift from the console.
COPY frontend-public/package*.json ./frontend-public/

WORKDIR /app/frontend-public
RUN npm ci

WORKDIR /app
COPY frontend-public ./frontend-public
COPY frontend/src ./frontend/src
COPY frontend/tailwind.config.js ./frontend/tailwind.config.js
COPY frontend/public ./frontend/public

WORKDIR /app/frontend-public
RUN npm run build

# The static files are served by the same server the operator's
# application uses in production.
RUN addgroup -g 1000 -S appgroup \
    && adduser -u 1000 -S appuser -G appgroup \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 5174

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5174 || exit 1

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5174"]
