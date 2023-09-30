import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="easy-visualiser",
    version="0.1.0",
    author="Tin Lai",
    author_email="oscar@tinyiu.com",
    description="Pluggable visualiser",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            # "plannerGraphVisualiser=plannerGraphVisualiser.marlin_monitor_main:run",
            # "viewDisplacementMap=plannerGraphVisualiser.view_displacement_map_main:run",
        ]
    },
    install_requires=[
        "numpy",
        "scipy",
        "overrides",
        "vispy",
        "pyqt6",
        "typed-argument-parser",
        "msgx",
    ],
    python_requires=">=3.7",
)
