# Add these cron jobs to your server

Sync services daily at 1 AM
0 1 * * * cd C:\Users\kpoje\Desktop\pysmart\engage\socialboost\core && python manage.py sync_services >> /var/log/socialboost/sync_services.log 2>&1

# Update order statuses every 15 minutes
*/15 * * * * cd C:\Users\kpoje\Desktop\pysmart\engage\socialboost\core && python manage.py update_order_statuses >> /var/log/socialboost/update_orders.log 2>&1