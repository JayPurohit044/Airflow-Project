from airflow.decorators import dag, task
from airflow.providers.sqlite.operators.sqlite import SqliteOperator
from airflow.providers.sqlite.hooks.sqlite import SqliteHook
import pendulum
import requests
import xmltodict
import os

@dag (
    dag_id = 'podcast_summary',
    schedule_interval = '@daily',
    start_date = pendulum.datetime(2024, 7, 17),
    catchup = False
)

def podcast_summary():
    
    create_database = SqliteOperator (
        task_id = 'create_table_sqlite',
        sql = """
        CREATE TABLE IF NOT EXISTS episodes (
            link text PRIMARY KEY,
            title text,
            filename text,
            published text,
            description text
        )
        """,
        sqlite_conn_id = "podcasts"
    )
    
    @task() #task flow it is turning it to python operator
            # This decorator turns below function to airflow task
    def get_episodes():
        data = requests.get("https://marketplace.org/feed/podcast/marketplace")
        feed = xmltodict.parse(data.text)
        episodes = feed['rss']['channel']['item']
        print(len(episodes))
        return episodes
    podcast_episodes = get_episodes()
    create_database.set_downstream(podcast_episodes)
    
    @task()
    def load_episodes(episodes):
        hook = SqliteHook(sqlite_conn_id = "podcasts")
        stored = hook.get_pandas_df("select * from episodes;")
        new_episodes = []
        for episode in episodes :
            # print(f"{episode['link'].split('/')[-1]}.mp3")
            if episode["link"] not in stored["link"].tolist():
                filename = f"{episode['link'].split('/')[-1]}.mp3"
                new_episodes.append([episode["link"], episode["title"], episode["pubDate"], episode["description"], filename])
        hook.insert_rows(table = "episodes", rows = new_episodes, target_fields = ["link", "title", "published", "description", "filename"])
    load_episodes(podcast_episodes)
    
    @task()
    def download_episodes(episodes):
        for episode in episodes[:2] :
            filename = f"{episode['link'].split('/')[-1]}.mp3"
            audio_path = os.path.join("episodes", filename)
            os.makedirs("episodes", exist_ok=True)
            print(os.path.abspath(audio_path))
            if not os.path.exists(audio_path):
                print(f"Downloading... {filename}")
                # audio = requests.get(episode["enclosure"]["@url"])
                # with open(audio_path, "wb+") as f:
                #     f.write(audio.content)
    download_episodes(podcast_episodes)
    
summary = podcast_summary()


# \\wsl.localhost\Ubuntu\home\guddu\Projects\Airflow\twitter_etl.py