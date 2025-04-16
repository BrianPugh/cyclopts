from cyclopts import App

app = App()


@app.command()
def check():
    pass


if __name__ == "__main__":
    app()
