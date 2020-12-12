Stores a user's files in the "cloud" (depending where you run the servers). The file is split between 4 servers such that only 2 servers are needed to recreate it. This is done by XORing pieces of the data and uploading pieces to specific servers. Multiple users can be created, each with access to their own files.

To test, on the server end you can run server/_makeservers.py, which will quickly start up all of the servers needed and connect them to each other. In a production environment you would start each node server on its own machine. To run the client, call "client.py IP PORT", replacing IP and PORT with those of the storageserver.py server. The default account is admin with password "admin".

<a href="url"><img src="https://github.com/malcolm-weathers/470_cloudstorage/blob/master/example.jpg?raw=true" align="left" height="400" ></a>
