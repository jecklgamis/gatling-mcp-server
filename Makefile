IMAGE_NAME:=gatling-mcp-server:main

default:
	@cat ./Makefile
install-deps:
	 @pip3 install -r requirements.txt
image:
	 docker build -t $(IMAGE_NAME) .
run:
	 @docker run -p 58090:58090 -it $(IMAGE_NAME)
run-shell:
	 @docker run -it $(IMAGE_NAME) /bin/bash
exec-shell:
	docker exec -it `docker ps | grep $(IMAGE_NAME) | awk '{print $$1}'` /bin/bash
all: check image
up: all run
check:
	 @pytest -s
clean:
	@find . -name "*.log" | xargs -r rm -f
