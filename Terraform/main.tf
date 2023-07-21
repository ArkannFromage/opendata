provider "aws" {

  region = var.region

}


resource "aws_iam_role" "lambda_role" {
  name               = "Open_Data_Role"
  assume_role_policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": "sts:AssumeRole",
     "Principal": {
       "Service": "lambda.amazonaws.com"
     },
     "Effect": "Allow",
     "Sid": ""
   }
 ]
}
EOF
}


resource "aws_iam_policy" "iam_policy_for_lambda" {

  name   = "open_data_aws_iam_policy"
  path   = "/"
  policy = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
     "Action": [
       "logs:CreateLogGroup",
       "logs:CreateLogStream",
       "logs:PutLogEvents"
     ],
     "Resource": "arn:aws:logs:*:*:*",
     "Effect": "Allow"
   },
   {
    "Action": [
        "s3:PutObject", 
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:GetObjectAcl"
     ],
     "Resource": "arn:aws:s3:::vwis-open-data-${lower(var.environment)}/*",
     "Effect": "Allow"
   }
 ]
}
EOF
}



resource "aws_iam_role_policy_attachment" "attach_iam_policy_to_iam_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_lambda.arn
}

resource "null_resource" "pip_install" {
  triggers = {
    shell_hash = "${sha256(file("${var.lambda_root}/requirements.txt"))}"
  }

  provisioner "local-exec" {
    command = "python3 -m pip install -r ${var.lambda_root}/requirements.txt -t ${var.lambda_root}"
  }
}

data "archive_file" "zip_the_python_code" {
  type        = "zip"
  source_dir  = var.lambda_root
  output_path = "${path.module}/lambda.zip"
  depends_on = [null_resource.pip_install]
}



resource "aws_lambda_function" "terraform_lambda_func" {
  filename      = "${path.module}/lambda.zip"
  function_name = "Open_Data_Lambda_Function"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.10"
  depends_on    = [aws_iam_role_policy_attachment.attach_iam_policy_to_iam_role, null_resource.pip_install]
  timeout = 60
  source_code_hash = data.archive_file.zip_the_python_code.output_base64sha256
}


resource "aws_s3_bucket" "open_data" {

  bucket = "${lower(var.bucket_name)}-${lower(var.environment)}"

}



resource "aws_s3_bucket_versioning" "open_data" {
  bucket = aws_s3_bucket.open_data.id
  versioning_configuration {
    status = "Disabled"
  }
}

