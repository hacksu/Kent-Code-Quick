FROM ruby:3.4.8
ENV LANG=C.UTF-8
ENV ENABLE_SERVICE_WORKER=false

WORKDIR /devdocs

RUN apt-get update && \
    apt-get -y install git nodejs libcurl4 && \
    gem install bundler && \
    rm -rf /var/lib/apt/lists/*

COPY devdocs/Gemfile devdocs/Gemfile.lock devdocs/Rakefile /devdocs/

RUN bundle config set path.system true && \
    bundle install && \
    rm -rf ~/.gem /root/.bundle/cache /usr/local/bundle/cache

COPY devdocs/ /devdocs/

COPY devdocs-boot.ru /devdocs/config.ru

COPY devdocs-root-tmpl.js.erb /devdocs/assets/javascripts/templates/pages/root_tmpl.js.erb
COPY devdocs-app.erb /devdocs/views/app.erb

RUN thor docs:download html css javascript dom && \
    rm -rf /tmp

EXPOSE 9292
CMD rackup -o 0.0.0.0
