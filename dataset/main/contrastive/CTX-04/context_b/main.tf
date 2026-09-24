provider "aws" {
  region = "us-west-2"  # Replace with your desired AWS region
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"  # Replace with your desired CIDR block
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
}

resource "aws_route_table" "rtb" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "172.16.0.0/16"  # Replace with your desired CIDR block
    gateway_id = aws_internet_gateway.gw.id
  }
}
