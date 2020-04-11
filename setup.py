import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lightroom_sync",
    version="0.0.1",
    author="Johannes Andersson",
    author_email="hello@thejoltjoker.com",
    description="A script to sync Ligthroom catalogs across multiple storage devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thejoltjoker/lightroom-sync",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    py_modules=['lightroom_sync'],
    install_requires=[
        'Click',
    ],
    entry_points='''
            [console_scripts]
            lightroom-sync=lightroom_sync.lightroom_sync:cli
        ''',
)
