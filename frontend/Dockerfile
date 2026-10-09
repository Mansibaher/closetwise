FROM node:22.14.0-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV API_INTERNAL_URL=http://backend:8000
RUN npm run build
RUN chown -R node:node /app
USER node
EXPOSE 3000
CMD ["npm", "run", "start"]
