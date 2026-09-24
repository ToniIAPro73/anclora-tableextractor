import React from "react";

export const BrandMark = ({ className = "" }) => (
  <img
    src="/brand/anclora-tableextractor.png"
    alt=""
    aria-hidden="true"
    className={`object-contain ${className}`}
  />
);
