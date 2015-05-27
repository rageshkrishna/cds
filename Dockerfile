FROM shipimg/appbase:latest

RUN mkdir -p /home/shippable/scripts
ADD . /home/shippable/cds

# need to add this since logs is ignored in .dockerignore
RUN mkdir -p /home/shippable/cds/logs

RUN mkdir -p /home/shippable/runtime/builds
RUN cd /home/shippable/cds/google-cloud-sdk && ./install.sh --usage-reporting=false --bash-completion=true --path-update=true
ENV PATH $PATH:/home/shippable/cds/google-cloud-sdk/bin
RUN gcloud components update preview

ENTRYPOINT ["/home/shippable/cds/boot.sh"]
