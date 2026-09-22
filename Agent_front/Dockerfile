FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps --no-audit --no-fund
COPY . .
RUN NODE_OPTIONS=--openssl-legacy-provider npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/ /usr/share/nginx/html/
EXPOSE 80
