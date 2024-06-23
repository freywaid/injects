import setuptools

with open("README.md", "rt") as f:
    long_description = f.read()

setuptools.setup(
    name="injects",
    version="0.0.1",
    author="Frey Waid",
    author_email="logophage1@gmail.com",
    description="Argument injection and composition",
    license="MIT license",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/freywaid/injects",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[],
)
