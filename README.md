To produce an Anilist token ready for your .env do the following:
1) Go to your anilist settings and create a new api client in developer settings
2) Insert your 'ID' into the '{clientID}' in the web address provided:
https://anilist.co/api/v2/oauth/authorize?client_id={clientID}&response_type=token
3) paste your given string inside of your .env

   Running:
0) Clone to your device if not already.
1) name it whatever you want and then find the path e.g:
cd Anilist_Manager
pwd
2)
cd "/paste/the/path/you/copied/here"
python3 app.py
3) it will run on local host 5001. You can change this inside of app.py at the very bottom to suit your needs. 
