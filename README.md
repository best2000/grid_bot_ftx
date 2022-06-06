# Instructions

### 1.Docker container setup
- in `Dockerfile` edit ENV with your `API_KEY` and `SECRET_KEY`
- do these steps
```shell
#build docker image
docker build -t <name>:<tag> .
#run container from image, interactive mode, auto delete, mapped host volume to check log data
docker run -it --rm -v <hostDirectoryName>:/app/public <imageId>
#now you are inside a running container
```
- **you must be inside a container(shell) by now!**

### 2.Edit config.ini
- edit bot parameters at `/app/config.ini`
```shell
#inside a container(shell)
nano /app/config.ini
```
### 3.Generate and customize grid.csv
- edit grid generator script at `/app/grid_gen.py` to your grid setup then run the script
```shell
#inside a container(shell)
#edit
nano /app/grid_gen.py
#generate
python /app/grid_gen.py
```
- you can still customize your generated grid at `/app/public/grid.csv` before start runing bot
- 
### 4.Start runing bot
```shell
#inside a container(shell)
python /app/main.py
```