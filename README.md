# Instructions

### 1. Docker container setup

-   in `Dockerfile` edit ENV with your `API_KEY` and `SECRET_KEY`
-   do these steps

```shell
#build docker image
docker build -t <name>:<tag> .
#run container from image, interactive mode, auto delete, mapped host volume to check log data
docker run -it --rm -v <hostDirectoryName>:/app/public <imageId> /bin/bash
```
- check host mapped volume for linux at `/var/lib/docker/volumes/`
- for windows at `\\wsl$\docker-desktop-data\version-pack-data\community\docker\volumes `

> **you must be inside a container(shell) by now!**

### 2. Edit config.ini

-   edit bot parameters at `/app/public/config.ini`

```shell
nano /app/public/config.ini
```

### 3. Generate and customize grid.csv

-   generate `grid.csv` from cli app at `/app/grid_gen.py`

```shell
#generate grid.csv
python /app/grid_gen.py <[OPTIONS]> <MIN_ZONE> <MAX_ZONE> <GAP_TYPE> <POS_TYPE> <POS_VAL>
```

-   after generated `grid.csv` you can still customize your generated grid at `/app/public/grid.csv` before start runing bot
-   if you want to visulize your `grid.csv`, you can plot image witl cli app at `/app/grid_plot.py` (it will plot image from `/app/public/grid.csv`)

```shell
#plot image from ./public/grid.csv (for preview)
python /app/grid_plot.py <[OPTIONS]> <MARKET_SYMBOL> <TIMEFRAME> <LIMIT>
```

### 4. Start runing bot

```shell
python /app/main.py
```
