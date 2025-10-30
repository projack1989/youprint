# youprint
YoPrint Laravel Coding Project Spec but I tried to work with Django 5.2.7
https://www.notion.so/YoPrint-Laravel-Coding-Project-Spec-1e50db99ea52806fa1fde6e8fdf73b89

Seek Jobstreet
https://id.jobstreet.com/id/job/88126873?token=1%7E45081ff0-e74d-4c0e-92d3-602b0c9db576&tracking=TMC-AppNotSuitable-asia-4-similarjobs

To run this application

Firts Step installation:

1. Install Python
  sudo apt-get install python
2. Create Virtual Enviroment on your Django Directory
   python3 -m venv Env
4. Instal PIP
5. Install Django
  pip install django
6. Install Daphne
  pip install daphne
7. Install Redis
   https://redis.io/docs/latest/operate/oss_and_stack/install/archive/install-redis/install-redis-on-linux/

Read this tutorial for more complete explanation
https://greenwebpage.com/community/how-to-install-django-web-framework-on-ubuntu-24-04/

Download code and save in your Python directory
1. Run Redis Server
2. Activate Python Virtual Enviroment
   source Env/bin/activate
3. move to youprint folder
   cd youprint
4. run Daphine Server
   daphne -p 8000 youprint.asgi:application
5. Open your browser and open http://127.0.0.1:8000/upload/
6. Upload .csv where download from this repo folder fileCsv
