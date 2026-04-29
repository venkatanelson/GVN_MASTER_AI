PS C:\Users\Gvn\OneDrive\Desktop\my_algo_project> python app.py
🚀 [GVN SIGNAL ENGINE] Monitoring Alpha Grid for Breakouts...
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://192.168.29.101:8080
Press CTRL+C to quit
192.168.29.101 - - [29/Apr/2026 12:37:12] "GET /api/broker-status HTTP/1.1" 404 -
192.168.29.101 - - [29/Apr/2026 12:37:12] "GET /api/gvn-scanner HTTP/1.1" 200 -
192.168.29.101 - - [29/Apr/2026 12:37:12] "GET /api/gvn-scanner HTTP/1.1" 200 -
192.168.29.101 - - [29/Apr/2026 12:37:15] "GET /api/gvn-scanner HTTP/1.1" 200 -
192.168.29.101 - - [29/Apr/2026 12:37:16] "GET /api/gvn-scanner HTTP/1.1" 200 -
192.168.29.101 - - [29/Apr/2026 12:37:19] "GET / HTTP/1.1" 302 -
[2026-04-29 12:37:19,995] ERROR in app: Exception on /user/1 [GET]
Traceback (most recent call last):
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\flask\app.py", line 1455, in wsgi_app
    response = self.full_dispatch_request()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\flask\app.py", line 869, in full_dispatch_request
    rv = self.handle_user_exception(e)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\flask\app.py", line 867, in full_dispatch_request
    rv = self.dispatch_request()
         ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\flask\app.py", line 852, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Gvn\OneDrive\Desktop\my_algo_project\app.py", line 123, in user_dashboard
    return render_template('user.html', user=user, broker_config=broker_config, decrypted_keys=decrypted_keys,
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\flask\templating.py", line 152, in render_template
    return _render(app, template, context)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\flask\templating.py", line 133, in _render
    rv = template.render(context)
         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\jinja2\environment.py", line 1295, in render
    self.environment.handle_exception()
  File "C:\Users\Gvn\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\jinja2\environment.py", line 942, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "C:\Users\Gvn\OneDrive\Desktop\my_algo_project\templates\user.html", line 462, in top-level template code
    {{ '🟢 ' + user.algo_status if user.algo_status == "ON" else '🔴 ' + user.algo_status }}
    ^^^^^^^^^^^^^^^^^^^^^^^^^
jinja2.exceptions.UndefinedError: '__main__.User object' has no attribute 'algo_status'
192.168.29.101 - - [29/Apr/2026 12:37:19] "GET /user/1 HTTP/1.1" 500 -
