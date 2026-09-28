FROM node:22-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV VITE_API_PROXY_TARGET=http://server:8000
EXPOSE 5173
CMD ["npm", "run", "dev"]
