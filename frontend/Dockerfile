FROM node:18-alpine as builder

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm ci --legacy-peer-deps

COPY . .

RUN npm run build

FROM nginx:alpine as production

RUN addgroup -g 1001 -S nginx-user \
    && adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginx-user -g nginx-user nginx-user \
    && chown -R nginx-user:nginx-user /var/cache/nginx /var/log/nginx /etc/nginx/conf.d

RUN rm /etc/nginx/conf.d/default.conf

COPY --from=builder --chown=nginx-user:nginx-user /app/dist /usr/share/nginx/html
COPY --chown=nginx-user:nginx-user nginx.conf /etc/nginx/conf.d/default.conf

RUN touch /var/run/nginx.pid \
    && chown -R nginx-user:nginx-user /var/run/nginx.pid

USER nginx-user

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
