"""
Worker and WorkerManager — thread ownership for VaultCore.

No module outside this package creates threads.
Workers consume tasks from the TaskManager and execute them.
"""
