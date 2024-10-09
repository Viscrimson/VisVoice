from setuptools import setup, find_packages

setup(
    name='VisVoice',
    version='0.1',
    packages=find_packages(),  # Automatically find and include all packages (__init__.py needed)
    install_requires=[
        'pynput==1.7.7',
        'six==1.16.0',
        # Add any other dependencies here
    ],
    extras_require={
        'dev': [
            # List of development dependencies (e.g., linters, formatters)
        ]
    },
    entry_points={
        'console_scripts': [
            'visvoice=visvoice:main',  # Replace with your main function if you have one
        ],
    },
)
