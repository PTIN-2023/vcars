#!/bin/bash

containers=$(docker ps -a | grep virtual-car | tail -n +2 | awk '{print $1}')

for container in $containers
do 
    echo "stopping container $container ..."
    docker stop $container 2> /dev/null
    
    echo "deleting container $container ..."
    docker rm $container 2> /dev/null  
done

images=$(docker images | grep virtual-car | tail -n +2 | awk '{print $1}')

for image in $images
do
    echo "deleting docker image $image ..."
    docker rmi $image 2> /dev/null
done

echo "building virtual-car docker image"
docker build -t virtual-car . 2> /dev/null

for car_number in {1..10}
do
    echo "creating virtual-car containter for car number $car_number"
    docker run -d --name virtual-car-$car_number virtual-car --id $car_number 2> /dev/null
done