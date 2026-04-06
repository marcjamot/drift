FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# Source is bind-mounted at runtime for hot reload; copy here for image-only builds
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
