from flask import Flask, render_template, request
from eo import get_satellite_image


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():

    result = None
    error = None

    if request.method == "POST":

        try:

            latitude = float(
                request.form["latitude"]
            )

            longitude = float(
                request.form["longitude"]
            )

            result = get_satellite_image(
                latitude,
                longitude
            )

        except Exception as e:

            print("ERROR:", repr(e))

            error = str(e)

    return render_template(
        "index.html",
        result=result,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)
