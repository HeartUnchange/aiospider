import os
import os.path as stdpath

from setuptools import setup

package_dir = os.path.dirname(os.path.realpath(__file__))
requirement_path = stdpath.join(package_dir, 'requirements.txt')
install_requires = []
if stdpath.isfile(requirement_path):
    with open(requirement_path) as f:
        install_requires = f.read().splitlines()

setup(name='aiospider',
      description='Python asyncio spider',
      author='hxzhao527',
      author_email='haoxiangzhao@outlook.com',
      version='0.0.2',
      packages=['aiospider', "examples"],
      python_requires='>=3.3',
      install_requires=install_requires
      )
