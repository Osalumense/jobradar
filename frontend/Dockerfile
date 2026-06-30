FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Build Nuxt 3 application
RUN npm run build

# Expose port 3078
EXPOSE 3078

ENV PORT=3078
ENV HOST=0.0.0.0

CMD ["node", ".output/server/index.mjs"]
