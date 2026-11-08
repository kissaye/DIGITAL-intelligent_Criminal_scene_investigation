FROM node:16-alpine AS potree
ARG POTREE_VERSION=1.8
ARG POTREE_REVISION=1d3f9c9bbaeb0e50bb094b64789905e1bd46b4a2
RUN apk add --no-cache git
RUN git clone --depth 1 --branch ${POTREE_VERSION} https://github.com/potree/potree.git /potree \
    && test "$(git -C /potree rev-parse HEAD)" = "${POTREE_REVISION}"
WORKDIR /potree
RUN npm install --ignore-scripts && npm run build

FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=
ARG VITE_USE_MOCK=false
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_USE_MOCK=${VITE_USE_MOCK}
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
COPY --from=potree /potree/build/potree /usr/share/nginx/html/vendor/potree/build/potree
COPY --from=potree /potree/libs/jquery /usr/share/nginx/html/vendor/potree/libs/jquery
COPY --from=potree /potree/libs/jquery-ui /usr/share/nginx/html/vendor/potree/libs/jquery-ui
COPY --from=potree /potree/libs/spectrum /usr/share/nginx/html/vendor/potree/libs/spectrum
COPY --from=potree /potree/libs/tween /usr/share/nginx/html/vendor/potree/libs/tween
COPY --from=potree /potree/libs/d3 /usr/share/nginx/html/vendor/potree/libs/d3
COPY --from=potree /potree/libs/proj4 /usr/share/nginx/html/vendor/potree/libs/proj4
COPY --from=potree /potree/libs/openlayers3 /usr/share/nginx/html/vendor/potree/libs/openlayers3
COPY --from=potree /potree/libs/i18next /usr/share/nginx/html/vendor/potree/libs/i18next
COPY --from=potree /potree/libs/jstree /usr/share/nginx/html/vendor/potree/libs/jstree
COPY --from=potree /potree/libs/other /usr/share/nginx/html/vendor/potree/libs/other
COPY --from=potree /potree/libs/plasio /usr/share/nginx/html/vendor/potree/libs/plasio
EXPOSE 80
