from setuptools import setup, find_packages

setup(
    name="TakeHomePayApp",
    version="0.1",
    packages=find_packages(),
    install_requires=open("requirements.txt").read().splitlines(),
    entry_points={
        "console_scripts": [
            "takehomepay=app.location_take_home_pay_app:main"
        ]
    }
)
