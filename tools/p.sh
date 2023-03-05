ps aux|grep server.py
netstat -nlp|grep 80
netstat -ln | grep ':80' >/dev/null && echo "服务状态正常，正在监听80端口" || echo "未检测到进程在运行"
