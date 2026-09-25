# BUILDER
FROM node:22-alpine AS builder

WORKDIR /frontend


COPY package.json package-lock.json ./

RUN npm ci


COPY . .


RUN npm run build


# PRODUCTION
FROM nginx:1.27-alpine AS production

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder \
    /frontend/dist \
    /usr/share/nginx/html


EXPOSE 80


CMD ["nginx", "-g", "daemon off;"]