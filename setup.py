from setuptools import find_packages, setup, find_packages


with open("README.md", "r") as f:
    description = f.read()

setup(
    name='controltheorylib',
    packages=find_packages(include=['controltheorylib']),
    version='0.1.4',
    description='Library for animating key control theory concepts',
    author='Jort Stammen',
    install_requires=[],
    long_description=description,
    license='MIT',
    long_description_content_type="text/markdown",
    url='https://github.com/JortStamme/Controltheorylibrary'
)