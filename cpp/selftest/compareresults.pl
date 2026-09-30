#!/usr/bin/perl

# selftest-compareresults.pl <new data> <reference data>

use strict;

my $retstatus = 0;

my $epsilon = 1.0E-10;
my $maxdelta = 0;

open my $local_fh, '<', $ARGV[0] or die "Can't open $ARGV[0]: $!";
my $newResults = resultsHash($local_fh);
close $local_fh;

open my $local_reffh, '<', $ARGV[1] or die "Can't open $ARGV[1]: $!";
my $refResults = resultsHash($local_reffh);
close $local_reffh;

foreach my $refKey (keys %$refResults) {
   if(exists($newResults->{$refKey})) {
      my $maxval = (abs($refResults->{$refKey})>=abs($newResults->{$refKey})?abs($refResults->{$refKey}):abs($newResults->{$refKey}));

      my $absdelta = abs($refResults->{$refKey} - $newResults->{$refKey});

      my $reldelta;
      my $delta;

      #print "item: $refKey\n";

      if($maxval > 0.0) {
      	$reldelta = $absdelta / $maxval;
      } else {
        $reldelta = 0.0;
      }

      $delta = ($absdelta <= $reldelta) ? $absdelta : $reldelta;
      if($delta > $maxdelta) {
         $maxdelta = $delta;
      }

      if($delta >= $epsilon) {
         print "$ARGV[0]: Significant difference for $refKey (reference: $refResults->{$refKey} new: $newResults->{$refKey} delta: $delta)\n";
         $retstatus = 1;
      } 
      delete $newResults->{$refKey};
   } else {
      print "$ARGV[0]: No corresponding value for $refKey\n";
      $retstatus = 1;
   }
}

foreach my $newKey (keys %$newResults) {
   print "$ARGV[0]: Found extra data item: $newKey -> $newResults->{$newKey}\n";
}

print "Maximum delta: $maxdelta\n";
exit $retstatus;

sub resultsHash {
   my $fd = shift;
   my %input;

   # Two kinds of line are collected:
   #
   #  1. per-estimator values, e.g.
   #        Literal Collision Estimate: min entropy = 0.126...
   #
   #  2. the final combined figures produced by main() rather than by any
   #     estimator:
   #        H_bitstring = <v>
   #        H_bitstring Per Symbol = <v>
   #        H_original = <v>
   #        Assessed min entropy: <v>
   #
   # Group 2 was previously not collected at all, so a fault confined to the
   # final combination (for instance dropping the n x H_bitstring term, or
   # failing to fold in H_original) left every collected value unchanged and
   # the comparison passed. The final figure is the number an assessment is
   # actually reported with, so it is the one that most needs checking.
   while( my $line = <$fd> ) {
      if ( $line =~ /(Estimate:|Assessed|^H_original|^H_bitstring)/i ) {
         # "<label> = <value>" covers the estimators and H_original /
         # H_bitstring; "<label>: <value>" covers "Assessed min entropy".
         # The " = " form is tried first so that estimator lines, which
         # contain both separators, keep the labels they have always had.
         if(($line =~ /^([^=]+) = ([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)$/ ) ||
            ($line =~ /^([^:=]+): ([-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?)$/ )) {
            my $label = $1;
            my $value = $2;

            $label =~ s/\s*$//;

            $input{"$label"} = $value;
            #print "$label -> $value\n";
         } 
      } 
   }

  return \%input; # return hash reference
}

