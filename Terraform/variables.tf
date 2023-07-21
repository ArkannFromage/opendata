variable "lambda_root" {
  type        = string
  description = "The relative path to the source of the lambda"
  default     = "../LambdaOpenData"
}

variable "environment" {}

variable "bucket_name"{}

variable "acl_value" {

  default = "private"

}

variable "region" {

  default = "eu-west-3"

}