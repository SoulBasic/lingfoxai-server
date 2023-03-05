netstat -nlp|grep 80|grep -v grep|awk '{print$7}' | awk  -F '/' '{print "kill -9 "$1}'|sh
sleep 1s
netstat -ln | grep ':80' >/dev/null && echo "停止失败，请手动检查服务进程状态" || echo "停止成功"
