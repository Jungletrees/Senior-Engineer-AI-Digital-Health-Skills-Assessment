"use client";
import React, { useEffect, useState } from 'react';

export default function HomePage() {
  const [html, setHtml] = useState('Loading...');

  useEffect(() => {
    fetch('http://localhost:5000/', { headers: { Accept: 'text/html' } })
      .then((res) => res.text())
      .then((data) => setHtml(data))
      .catch(() => setHtml('Failed to load home page.'));
  }, []);

  return (
    <div dangerouslySetInnerHTML={{ __html: html }} />
  );
}
