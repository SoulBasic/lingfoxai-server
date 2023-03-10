cd ../src
nohup python3 ./server.py > ..//log/nohup_run.log 2>&1 &
sleep 1s
netstat -ln | grep ':80' >/dev/null && echo "启动成功" || echo "启动失败"
