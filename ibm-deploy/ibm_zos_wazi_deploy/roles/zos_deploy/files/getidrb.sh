#!/bin/sh
#*******************************************************************************
# Licensed Materials - Property of IBM
# (c) Copyright IBM Corp. 2022. All Rights Reserved.
#
# Note to U.S. Government Users Restricted Rights:
# Use, duplication or disclosure restricted by GSA ADP Schedule
# Contract with IBM Corp.
#*******************************************************************************

PRGPATH="`dirname "$0"`"
export LIBPATH=$LIBPATH:/usr/lib
$PRGPATH/getidrb $*
